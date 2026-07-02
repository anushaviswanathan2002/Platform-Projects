require "json"
require_relative "todo/version"

module Todo
  class Item
    attr_reader :id, :title, :done

    def initialize(id, title, done: false)
      @id = id
      @title = title
      @done = done
    end

    def done?
      @done
    end

    def complete!
      @done = true
    end

    def to_h
      { "id" => @id, "title" => @title, "done" => @done }
    end

    def self.from_h(hash)
      new(hash["id"], hash["title"], done: hash["done"])
    end
  end

  class List
    attr_reader :items

    def initialize(items = [])
      @items = items
      @next_id = items.empty? ? 1 : items.map(&:id).max + 1
    end

    def add(title)
      raise ArgumentError, "title cannot be empty" if title.nil? || title.strip.empty?
      id = @next_id
      @next_id += 1
      @items << Item.new(id, title)
      id
    end

    def complete(id)
      item = @items.find { |i| i.id == id }
      raise ArgumentError, "no item with id=#{id}" if item.nil?
      item.complete!
    end

    def remove(id)
      before = @items.length
      @items.reject! { |i| i.id == id }
      raise ArgumentError, "no item with id=#{id}" if @items.length == before
      @next_id = items.map(&:id).max + 1 unless @items.empty?
      true
    end

    def pending
      @items.reject(&:done?)
    end

    def to_json(*_args)
      { "items" => @items.map(&:to_h) }.to_json
    end
  end
end
